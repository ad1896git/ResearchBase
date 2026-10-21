"""B23 technical PostgreSQL evidence; exact immutable novelty history."""

from dataclasses import replace
from uuid import uuid4

from sqlalchemy import text

from researchbase.application.internal_review import (
    InternalReviewService,
    NoveltyReviewReadback,
    ReviewIssueRequest,
)
from researchbase.application.novelty import (
    RecordNoveltyAssessmentCommand,
    RecordSearchCoverageCommand,
)
from researchbase.application.revision_action import (
    RecordConcernReReviewCommand,
    RecordNoveltyRevisionCommand,
    RevisionActionService,
)
from researchbase.domain.novelty import NoveltyOutcome


def _root(e):
    cov = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
        ),
    )
    command = RecordNoveltyAssessmentCommand(
        uuid4(),
        e["project"],
        e["claim"],
        cov.id,
        NoveltyOutcome.INCONCLUSIVE,
        "Insufficient selected coverage.",
    )
    return command, e["service"].record_novelty_assessment(e["author"], command)


def _review(e, target, request=None, issues=None):
    service = InternalReviewService(e["factory"], e["credentials"], e["literature"])
    view = service.create(
        e["reviewer"],
        e["project"],
        "NOVELTY_ASSESSMENT",
        target.id,
        "LITERATURE",
        "UNCERTAIN",
        "Independent review.",
        (ReviewIssueRequest("BLOCKING", "NOVELTY", "Reassess the selected scope."),)
        if issues is None
        else issues,
        request or uuid4(),
    )

    assert isinstance(view, NoveltyReviewReadback)
    return service, view


def test_exact_review_replay_and_history(novelty_env):
    e = novelty_env
    command, root = _root(e)
    request = uuid4()
    service, review = _review(e, root, request)
    assert isinstance(review, NoveltyReviewReadback)
    assert review.material_version == 2
    assert review.target.id == root.id
    assert review.target_content_hash == root.content_hash
    assert review.issues[0].status == "OPEN"
    assert _review(e, root, request)[1].content_hash == review.content_hash
    successor = e["service"].record_novelty_assessment(
        e["author"], replace(command, id=uuid4(), supersedes_assessment_id=root.id)
    )
    history = service.read(e["reviewer"], e["project"], review.id)
    assert isinstance(history, NoveltyReviewReadback)
    assert history.target.superseded_by_assessment_id == successor.id
    assert history.content_hash == review.content_hash
    with e["engine"].connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM review_issue_events WHERE issue_id=:id"),
                {"id": review.issues[0].id},
            ).scalar_one()
            == 1
        )


def test_completed_revision_and_exact_correspondence(novelty_env):
    e = novelty_env
    command, root = _root(e)
    _, review = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(command, id=uuid4(), supersedes_assessment_id=root.id)
    )
    service = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    action_command = RecordNoveltyRevisionCommand(
        uuid4(), e["project"], review.issues[0].id, result.id
    )
    action = service.record_novelty_revision(e["author"], action_command)
    assert action.result.id == result.id
    assert (
        service.record_novelty_revision(e["author"], action_command).content_hash
        == action.content_hash
    )
    _, new_review = _review(e, result, issues=())
    link = service.record_concern_re_review(
        e["reviewer"],
        RecordConcernReReviewCommand(e["project"], action.id, new_review.id),
        novelty=True,
    )
    assert link.review.recommendation == "UNCERTAIN"
    assert (
        service.read_novelty_re_review(
            e["reviewer"], e["project"], action.id, new_review.id
        ).action.id
        == action.id
    )
    assert (
        service.read_revision_action(e["author"], e["project"], action.id).content_hash
        == action.content_hash
    )
    with e["engine"].connect() as c:
        assert (
            c.execute(
                text("SELECT status FROM review_issues WHERE id=:id"), {"id": review.issues[0].id}
            ).scalar_one()
            == "OPEN"
        )


def test_positive_selected_basis_and_comparison_correction_history(novelty_env):
    from tests.integration.phase2.b19_basis_support import record, setup

    e = novelty_env
    command, relation_command, relation, _ = setup(e)
    assessment = record(e, command)
    service, review = _review(e, assessment)
    assert review.target.material_version == 2
    assert review.target.search_coverage.material_version == 2
    assert review.target.prior_art_basis[0].prior_art_relation.id == relation.id
    assert review.target.search_coverage.quality.captured_unresolved_result_count is not None
    e["service"].record_prior_art_relation(
        e["author"],
        replace(relation_command, id=uuid4(), supersedes_prior_art_relation_id=relation.id),
    )
    history = service.read(e["reviewer"], e["project"], review.id)
    assert history.content_hash == review.content_hash
    assert isinstance(history, NoveltyReviewReadback)
    assert not history.target.current_validity.usable_for_current_judgment
    assert _review(e, assessment)[1].target_content_hash == assessment.content_hash


def test_legacy_null_capture_and_new_zero_capture_stay_distinct(novelty_env):
    from alembic import command
    from alembic.config import Config

    from tests.integration.phase2.b19_basis_support import legacy_coverage

    e = novelty_env
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "0067_b17_prepared_package_freeze")
    legacy = legacy_coverage(e)
    command.upgrade(cfg, "head")
    zero = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], (e["executions"][1],), "Zero returned results"
        ),
    )
    for coverage, expected in ((legacy, None), (zero, 0)):
        assessment = e["service"].record_novelty_assessment(
            e["author"],
            RecordNoveltyAssessmentCommand(
                uuid4(),
                e["project"],
                e["claim"],
                coverage.id,
                NoveltyOutcome.INCONCLUSIVE,
                "Bounded historical coverage",
            ),
        )
        _, review = _review(e, assessment)
        assert review.target.search_coverage.quality.captured_unresolved_result_count == expected
        assert review.target.search_coverage.material_version == (1 if expected is None else 2)
        assert review.target_content_hash == assessment.content_hash
